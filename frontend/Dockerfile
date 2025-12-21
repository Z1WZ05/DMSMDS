# Build stage
# 使用国内镜像源替换 node:18
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/node:18 AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
# 使用国内镜像源替换 nginx:stable-alpine
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/nginx:stable-alpine AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]