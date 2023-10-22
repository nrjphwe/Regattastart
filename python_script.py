import requests

php_url = 'http://regattastart.local/php_page.php'
response = requests.get(php_url)
cookies = response.cookies
user_name = requests.get(php_url, cookies=cookies).text

print(f"User's Name: {user_name}")
