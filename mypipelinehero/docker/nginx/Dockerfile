# Lightweight nginx image for local wildcard subdomain routing.
# Config is mounted from docker/nginx/conf.d/ in compose, so this image
# only needs the base nginx binary and a sensible default.
FROM nginx:1.27-alpine

# Remove the stock default so our conf.d/*.conf is the only server block.
RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80
