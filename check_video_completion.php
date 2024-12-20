<?php
    include_once 'functions.php';
    // Read the content of the status file
    $status = trim(file_get_contents('/var/www/html/status.txt'));
    console_log("check_video_completion, Line 13: isVideo1Completed status= " . $status);
    // Check if the status indicates Video1 completion
    echo $status;
?>