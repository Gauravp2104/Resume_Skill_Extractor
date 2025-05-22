FROM node:18

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

CMD ["npm", "start"]

RUN chmod -R 755 /app/src && \
    chown -R node:node /app