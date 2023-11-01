# ProductsWithREST_API

### Start

    make devenv
    make postgres
    source env/bin/activate
    products_app-db upgrade head
    products_app-api

### Deploy

    cd deploy
    ansible-playbook -i hosts.ini deploy.yml
