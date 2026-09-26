FROM node:21.7.1-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build
CMD ["sh", "-c", "cp -r /app/build/. /frontend_static/"]
