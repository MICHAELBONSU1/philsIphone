from app import app
with app.test_request_context('/messages'):
    app.jinja_env.get_template('messages.html')
print('TEMPLATE OK')
