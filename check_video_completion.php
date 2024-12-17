<?php
    function console_log($output, $with_script_tags = true) {
        $js_code = 'console.log(' . json_encode($output, JSON_HEX_TAG) .');';
        if ($with_script_tags) {
            $js_code = '<script>' . $js_code . '</script>';
        }
        echo $js_code;
    }
?>
<?php
    // Read the content of the status file
    $status = trim(file_get_contents('/var/www/html/status.txt'));
    console_log("check_video_completion, Line 13: isVideo1Completed status= " . $status);
    // Check if the status indicates Video1 completion
    echo $status;
?>