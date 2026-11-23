FROM python:3.12-slim
WORKDIR /app
COPY core/ /app/core/
COPY server/app.py server/core_bridge.py server/project_monitor.py server/project_inventory.json /app/
ENV PYTHONPATH=/app/core
EXPOSE 8080
CMD ["python","app.py"]
