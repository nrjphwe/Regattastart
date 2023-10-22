<!DOCTYPE html>
<html>
<head>
    <title>PHP to Python with AJAX</title>
</head>
<body>
    <form id="data-form">
        <label for="name">Name:</label>
        <input type="text" name="name" id="name">
        <input type="submit" value="Submit">
    </form>

    <div id="result"></div>

    <script>
        document.getElementById("data-form").addEventListener("submit", function (e) {
            e.preventDefault();
            
            var name = document.getElementById("name").value;

            // Create an XMLHttpRequest object
            var xhr = new XMLHttpRequest();

            // Define the callback function to handle the response
            xhr.onload = function () {
                if (xhr.status === 200) {
                    document.getElementById("result").innerHTML = xhr.responseText;
                } else {
                    document.getElementById("result").innerHTML = "Error: " + xhr.status;
                }
            };

            // Prepare and send the request
            xhr.open("POST", "/cgi-bin/python_script.py", true);
            xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
            xhr.send("name=" + name);
        });
    </script>
</body>
</html>
