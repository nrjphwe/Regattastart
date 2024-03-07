<script>
function isVideo1Completed() {
    // Read the content of the status file
    $status = trim(file_get_contents('/var/www/html/status.txt'));
    error_log("check_video_completion, Line 39: isVideo1Completed status= " . $status);
    // Check if the status indicates Video1 completion
    return ($status === 'complete');
}
// Check Video1 completion status
$video1Completed = isVideo1Completed();
</script>