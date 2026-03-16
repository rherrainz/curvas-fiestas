web: sh -c 'cd src && python manage.py migrate && gunicorn retail_curves.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 300'
