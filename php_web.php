<?php
session_start(); // Start the session
?>
<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $_SESSION['user_name'] = $_POST['name'];
    echo "User's Name (in PHP): " . $_SESSION['user_name']; // Debugging output
    header('Location: /cgi-bin/python_script.py'); // Redirect to the Python script
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
    <?php
    // Check if user_name is set in the session
    if (isset($_SESSION['user_name'])) {
        $user_name = $_SESSION['user_name'];
        echo "<p>User's Name: $user_name</p>";
    }
    ?>
</body>
</html>
