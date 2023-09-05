web: gunicorn final6.wsgi:application --log-file -
worker: celery -A final6 worker -l info  
beat: celery -A final6 beat -l info      
