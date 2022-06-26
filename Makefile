PROJECT_NAME ?= products_app
VERSION = $(shell python3 setup.py --version | tr '+' '-')
PROJECT_NAMESPACE ?= theantialex
REGISTRY_IMAGE ?= $(PROJECT_NAMESPACE)/$(PROJECT_NAME)

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
	
sdist: clean
	# официальный способ дистрибуции python-модулей
	python3 setup.py sdist

docker: sdist
	docker build -t $(PROJECT_NAME):$(VERSION) .

upload: docker
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):$(VERSION)
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):latest
	docker push $(REGISTRY_IMAGE):$(VERSION)
	docker push $(REGISTRY_IMAGE):latest