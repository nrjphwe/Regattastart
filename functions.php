<?php
// sudo cp functions.php /var/www/html/
if (!function_exists('console_log')) {
    function console_log($message) {
        echo "<script>console.log(". json_encode($message) .");</script>";
    }
}
// Set the logging level for Python scripts
putenv("LOG_LEVEL=INFO");  // You can change to "INFO", "WARNING", or other levels as needed
?>