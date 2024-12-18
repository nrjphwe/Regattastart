<?php
function console_log($message) {
    echo "<script>console.log('" . addslashes($message) . "');</script>";
}
?>