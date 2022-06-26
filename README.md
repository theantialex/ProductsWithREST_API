# ProductsWithREST_API

### Запуск

    make devenv
    make postgres
    source env/bin/activate
    products_app-db upgrade head
    products_app-api

### Деплой

    cd deploy
    ansible-playbook -i hosts.ini --user=root deploy.yml