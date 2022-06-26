############### Образ для сборки виртуального окружения ################
# Основа — «тяжелый» (~1 ГБ, в сжатом виде ~500 ГБ) образ со всеми необходимыми
# библиотеками для сборки модулей
FROM snakepacker/python:all as builder

# Создаем виртуальное окружение и обновляем pip
RUN python3.8 -m venv /usr/share/python3/app
RUN /usr/share/python3/app/bin/pip install -U pip

# Устанавливаем зависимости отдельно, чтобы закешировать. При последующей сборке
# Docker пропустит этот шаг, если requirements.txt не изменится
COPY requirements.txt /mnt/dist/
RUN /usr/share/python3/app/bin/pip install -Ur /mnt/dist/requirements.txt

# Копируем source distribution в контейнер и устанавливаем его
COPY dist/ /mnt/dist/
RUN cd /mnt/dist/ && tar -xf *.tar.gz --strip-components 1
RUN /usr/share/python3/app/bin/pip install /mnt/dist/ \
    && /usr/share/python3/app/bin/pip check

RUN ln -snf /usr/share/python3/app/bin/products_app-* /usr/local/bin/

# Устанавливаем выполняемую при запуске контейнера команду по умолчанию
CMD ["products_app-api"]