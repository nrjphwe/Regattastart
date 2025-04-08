<?php
// Specify the correct path to the named pipe
// Ensure the named pipe has the correct permissions (chmod 666)
$pipePath = '/var/www/html/tmp/stop_recording_pipe';
include_once 'functions.php';
// Open the named pipe for writing
$pipeHandle = fopen($pipePath, 'w');
if ($pipeHandle === false) {
    // Handle error
    $lastError = error_get_last();
    error_log('Stop_recording.php Failed to open named pipe: ' . $lastError['message']);
    die('Failed to open named pipe.');
} else {
    error_log('Stop_recording.php Opened pipe handle successfully: ' . $pipeHandle);
}

$message = "stop_recording\n";
if (fwrite($pipeHandle, $message) === false) {
    // Log error if writing to pipe fails
    error_log('Stop_recording.php Failed to write message to named pipe.');
} else {
    // Log success message
    error_log('Stop_recording.php Message sent to named pipe: ' . $message);
}

if (fclose($pipeHandle) === false) {
    error_log('Stop_recording.php Failed to close pipe.');
} else {
    // Log success message
    error_log('Stop_recording.php succesfully closed the pipe:');
}
?>