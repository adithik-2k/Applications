FROM nginx:alpine

# Copy index.html
COPY index.html /usr/share/nginx/html/index.html.template

# Use a shell script to replace the variable and start nginx
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_URL}' < /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html && nginx -g 'daemon off;'"]
