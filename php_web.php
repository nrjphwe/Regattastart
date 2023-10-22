<?php
session_start(); // Start the session

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $_SESSION['user_name'] = $_POST['name'];
    header('Location: python_script.php'); // Redirect to the Python script
    exit();
}
?>

<!DOCTYPE html>
<html>
<head>
    <title>PHP to Python</title>
</head>
<body>
    <form method="post" action="">
        <label for="name">Name:</label>
        <input type="text" name="name" id="name">
        <input type="submit" value="Submit">
    </form>
</body>
</html>
