# 使用官方的 Python 镜像作为基础镜像
FROM python:3.10

COPY . /app

# 安装项目依赖
RUN pip install -r /app/requirements.txt

WORKDIR /app


RUN ls /app
EXPOSE 8080

# change the entrypoint to the python script 
CMD ["python", "grid_trading.py"]