# The whole app is stdlib Python plus three static files, so there is nothing
# to install and nothing to build.
FROM python:3.12-alpine

WORKDIR /app
COPY server.py index.html showcase.html ./
COPY fontkit.js app.js showcase.js style.css showcase.css ./
COPY fonts/ ./fonts/

# Uploads land in a separate directory so a volume mounted there cannot hide
# the fonts shipped in the image.
ENV FONT_UPLOADS=/data/fonts
RUN mkdir -p /data/fonts

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/fonts').read()" || exit 1

CMD ["sh", "-c", "python server.py --host 0.0.0.0 --port 8000 --fonts /app/fonts --uploads $FONT_UPLOADS"]
