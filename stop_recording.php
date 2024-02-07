<?php
// Specify the correct path to the named pipe
$pipePath = '/var/www/html/tmp/stop_recording_pipe';

// Open the named pipe for writing
$pipeHandle = fopen($pipePath, 'w');
if ($pipeHandle === false) {
    // Handle error
    $lastError = error_get_last();
    error_log('Failed to open named pipe: ' . $lastError['message']);
    die('Failed to open named pipe.');
} else {
    error_log('Opened pipe handle successfully: ' . $pipeHandle);
}

$message = 'stop_recording';
if (fwrite($pipeHandle, $message) === false) {
    // Log error if writing to pipe fails
    error_log('Failed to write message to named pipe.');
} else {
    // Log success message
    error_log('Message sent to named pipe: ' . $message);
}

if (fclose($pipeHandle) === false) {
    error_log('Failed to close pipe.');
} else {
    // Log success message
    error_log('succesfully closed the pipe: ' . $pipeHandle);
}

?>