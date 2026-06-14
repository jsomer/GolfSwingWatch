from __future__ import annotations

from datetime import date
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from analysis.movement_viz import find_swing, load_raw_swings, movement_catalog, movement_payload

from .data_access import load_features


def _apply_filters(
    records,
    clubs: list[str] | None,
    ratings: list[int] | None,
    start_date: date | None,
    end_date: date | None,
):
    filtered = records.copy()
    if clubs and "club" in filtered.columns:
        filtered = filtered[filtered["club"].isin(clubs)]
    if ratings and "rating" in filtered.columns:
        filtered = filtered[filtered["rating"].isin(ratings)]
    if start_date and "date_only" in filtered.columns:
        filtered = filtered[filtered["date_only"] >= start_date]
    if end_date and "date_only" in filtered.columns:
        filtered = filtered[filtered["date_only"] <= end_date]
    return filtered


def _parse_origins(raw: str | None) -> list[str]:
    if not raw:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [value.strip() for value in raw.split(",") if value.strip()]


def _auth_dependency(api_key: str | None):
    def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if not api_key:
            return
        if x_api_key != api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    return require_api_key


def create_app(
    features_path: str | None = None,
    raw_swings_path: str | None = None,
    api_key: str | None = None,
    allowed_origins: list[str] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="GolfSwingWatch Analysis API",
        version="0.1.0",
        description="Query and summarize swing feature tables for browser dashboards.",
    )
    cors_origins = allowed_origins or _parse_origins(os.getenv("ALLOWED_ORIGINS"))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )
    require_api_key = _auth_dependency(api_key if api_key is not None else os.getenv("API_KEY"))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/summary")
    def summary(
        _: None = Depends(require_api_key),
        clubs: list[str] | None = Query(default=None),
        ratings: list[int] | None = Query(default=None),
        start_date: date | None = Query(default=None),
        end_date: date | None = Query(default=None),
    ) -> dict[str, Any]:
        try:
            frame = load_features(features_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        filtered = _apply_filters(frame, clubs, ratings, start_date, end_date)
        if filtered.empty:
            return {
                "swings": 0,
                "avg_rating": None,
                "avg_tempo_ratio": None,
                "avg_peak_rotational_velocity": None,
                "clubs": [],
                "ratings": [],
            }

        return {
            "swings": int(len(filtered)),
            "avg_rating": float(filtered["rating"].mean()) if "rating" in filtered.columns else None,
            "avg_tempo_ratio": float(filtered["tempo_ratio"].mean())
            if "tempo_ratio" in filtered.columns
            else None,
            "avg_peak_rotational_velocity": float(filtered["peak_rotational_velocity"].mean())
            if "peak_rotational_velocity" in filtered.columns
            else None,
            "clubs": sorted([str(v) for v in filtered["club"].dropna().unique()])
            if "club" in filtered.columns
            else [],
            "ratings": sorted([int(v) for v in filtered["rating"].dropna().unique()])
            if "rating" in filtered.columns
            else [],
        }

    @app.get("/records")
    def records(
        _: None = Depends(require_api_key),
        limit: int = Query(default=200, ge=1, le=5000),
        clubs: list[str] | None = Query(default=None),
        ratings: list[int] | None = Query(default=None),
        start_date: date | None = Query(default=None),
        end_date: date | None = Query(default=None),
    ) -> dict[str, Any]:
        try:
            frame = load_features(features_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        filtered = _apply_filters(frame, clubs, ratings, start_date, end_date).copy()
        if "date" in filtered.columns:
            filtered = filtered.sort_values("date", ascending=False)
        filtered = filtered.head(limit)

        serializable = filtered.copy()
        if "date" in serializable.columns:
            serializable["date"] = serializable["date"].astype(str)
        if "date_only" in serializable.columns:
            serializable["date_only"] = serializable["date_only"].astype(str)
        serializable = serializable.where(serializable.notna(), None)

        return {"count": int(len(serializable)), "items": serializable.to_dict(orient="records")}

    @app.get("/movement/swings")
    def movement_swings(_: None = Depends(require_api_key)) -> dict[str, Any]:
        try:
            records = load_raw_swings(raw_swings_path or os.getenv("RAW_SWINGS_PATH"))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        items = movement_catalog(records)
        return {"count": len(items), "items": items}

    @app.get("/movement/{swing_id}")
    def movement_detail(swing_id: str, _: None = Depends(require_api_key)) -> dict[str, Any]:
        try:
            records = load_raw_swings(raw_swings_path or os.getenv("RAW_SWINGS_PATH"))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        record = find_swing(records, swing_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Swing not found: {swing_id}")
        return movement_payload(record)

    return app


app = create_app(
    features_path=os.getenv("FEATURE_TABLE_PATH"),
    raw_swings_path=os.getenv("RAW_SWINGS_PATH"),
)
