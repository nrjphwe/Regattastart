<?php
// sudo cp functions.php /var/www/html/
function console_log($message) {
    echo "<script>console.log('" . addslashes($message) . "');</script>";
}
?>