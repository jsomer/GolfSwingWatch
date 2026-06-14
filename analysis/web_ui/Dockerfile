FROM node:20-alpine AS build

WORKDIR /app

COPY analysis/web_ui/package*.json /app/
RUN npm install

COPY analysis/web_ui /app
ARG VITE_API_BASE=/api
ARG VITE_API_KEY=
ENV VITE_API_BASE=$VITE_API_BASE
ENV VITE_API_KEY=$VITE_API_KEY
RUN npm run build

FROM nginx:1.27-alpine
COPY analysis/web_ui/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
