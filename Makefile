clean:
	rm -fr *.egg-info dist

devenv: clean
	rm -rf env
	# создаем новое окружение
	python3 -m venv env
	# обновляем pip
	env/bin/pip install -U pip
	# устанавливаем основные + dev зависимости
	env/bin/pip install -Ue '.[dev]'

postgres:
	docker stop products-db || true
	docker run --rm --detach --name=products-db \
		--env POSTGRES_USER=db_user \
		--env POSTGRES_PASSWORD=12345 \
		--env POSTGRES_DB=products \
		--publish 5432:5432 postgres