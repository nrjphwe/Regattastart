<?php
    header("Access-Control-Allow-Origin: http://78.79.198.9"); // eller ange specifik domän istället för '*'
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    header("Access-Control-Allow-Headers: Content-Type");
    include_once 'functions.php';
    // Read the content of the status file
    $status = trim(file_get_contents('/var/www/html/status.txt'));
    console_log("check_video_completion, Line 13: isVideo1Completed status= " . $status);
    // Check if the status indicates Video1 completion
    echo $status;
?>