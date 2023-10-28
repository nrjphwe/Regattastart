<?php
session_start();
print_r($_SESSION);
echo "<br/>";
print_r($_POST);
echo "<br/>";
ini_set('display_errors', 1);
error_reporting(E_ALL);
?>

<?php
function generateUniqueID() {
    // Generate a unique ID based on the current timestamp and a random number
    $timestamp = time();
    $random = mt_rand(1000, 9999); // Generate a random 4-digit number
    $race_id = "{$timestamp}_{$random}";
    return $race_id;
}
?>

<?php
    // using a file based approach, to be able to use several devices.
    $race_id = generateUniqueID(); // Function to generate a unique ID
    $data = $_POST; // Data submitted by the user
    $data_json = json_encode($data);
    $file_path = "/var/www/html/{$race_id}.json"; // Adjust the file path
    file_put_contents($file_path, $data_json);
?>

<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Process and store the form data
    $_SESSION["form_data"] = $_POST;

    // Execute the Python script
    //exec('python3 /usr/lib/cgi-bin/regattastart6.py ' . escapeshellarg(json_encode($_POST)) . ' &');
    $command = 'python3 /usr/lib/cgi-bin/regattastart6.py ' . escapeshellarg(json_encode($_POST)) . ' > /var/www/html/output.txt 2>&1 &';
    shell_exec($command);
    echo date('h:i:s') . "<br>";
    echo "execution started";
    sleep(3);
    //exec('python3 /usr/lib/cgi-bin/regattastart6.py ' . escapeshellarg(json_encode($_POST)));
    
    // Redirect to index.php
    header("Location: index.php");
    exit;
}
?>

<!DOCTYPE html>
<html>
<div align="center">
<head><title> Regattastart 1 för setup av en start </title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/w3.css"
</head>
<div class="w3-container w3-green">
<h2>Regattastart 1 för setup av en start</h2>
</div>
<!-- Here is our main header that is used across all the pages of our website -->
<meta http-equiv="refresh" content="200" >
<header>
</div>
<div align="center">
<?php
    // output index6.php was last modified.
    $filename = 'index6.php';
    if (file_exists($filename)) {
        echo "This page: $filename was modified: " . date ("Y-m-d H:i:s.", filemtime($filename));
    }
?>
        
<!-- HTML form -->
<body>
<div align="center">
<form action="index6.php" method="POST">
     <!-- Your form fields -->
    <div class="w3-row-padding" align="center">
    <div class="w3-half" align="center">
        <fieldset>
            <h4>Day and time setup</h4>
            <div data-tap-disabled="true">
            Start Time: <select name = "start_time" id = "start_time">
            <?php
                $hour = date('H');
                $steps   = 10; // only edit the minutes value
                $current = 0;
                $loops   = 24*(60/$steps);
                //$loops   = (24-$hour)*(60/$steps);
                //for ($i = $hour*(60/$steps); $i < $loops; $i++) {
                for ($i = 0; $i < $loops; $i++) {
                //    $time = sprintf('%02d:%02d', $i/(60/$steps), $current%60);
                $start_time = sprintf('%02d:%02d', $i/(60/$steps), $current%60);
                //echo '<option>' . $start_time . '</option>';
                echo '<option value="' . $start_time . '">' . $start_time . '</option>';
                $current += $steps;
                }
            ?>
            </select>
            </div><p>
            <?php $day = date("l") 
            ?>
            Day for race <select name = "day" id="day">
            <option <?php if(isset($day) && $day == "Monday"){echo "selected=\"selected\"";} ?> value="Monday">Monday</option>
            <option <?php if(isset($day) && $day == "Tuesday"){echo "selected=\"selected\"";} ?> value="Tuesday">Tuesday</option>
            <option <?php if(isset($day) && $day == "Wednesday"){echo "selected=\"selected\"";} ?> value="Wednesday">Wednesday</option>
            <option <?php if(isset($day) && $day == "Thursday"){echo "selected=\"selected\"";} ?> value="Thursday">Thursday</option>
            <option <?php if(isset($day) && $day == "Friday"){echo "selected=\"selected\"";} ?> value="Friday">Friday</option>
            <option <?php if(isset($day) && $day == "Saturday"){echo "selected=\"selected\"";} ?> value="Saturday">Saturday</option>
            <option <?php if(isset($day) && $day == "Sunday"){echo "selected=\"selected\"";} ?> value="Sunday">Sunday</option>
            </select>
        </fieldset>
    </div>
    <div class="w3-half" align="center">
        <fieldset>
            <h4>Video Setup</h4>
            <p></p>
            Duration between start and estimated finish: <select name = "video_delay" id = "video_delay">
            <option <?php if(isset($video_delay) && $video_delay == "3"){echo "selected=\"selected\"";} ?> value="3">3</option>
            <option <?php if(isset($video_delay) && $video_delay == "20"){echo "selected=\"selected\"";} ?> value="20">20</option>
            <option <?php if(isset($video_delay) && $video_delay == "30"){echo "selected=\"selected\"";} ?> value="30">30</option>
            <option <?php if(isset($video_delay) && $video_delay == "40"){echo "selected=\"selected\"";} ?> value="40">40</option>
            <option <?php if(isset($video_delay) && $video_delay == "50"){echo "selected=\"selected\"";} ?> value="50">50</option>
            <option <?php if(isset($video_delay) && $video_delay == "60"){echo "selected=\"selected\"";} ?> value="60">60</option>
            <option <?php if(isset($video_delay) && $video_delay == "70"){echo "selected=\"selected\"";} ?> value="70">70</option>
            <option <?php if(isset($video_delay) && $video_delay == "80"){echo "selected=\"selected\"";} ?> value="80">80</option>
            </select>
            <p></p>
            Duration for each video: <select name = "video_dur" id = "video_dur">
            <option <?php if(isset($video_dur) && $video_dur == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
            <option <?php if(isset($video_dur) && $video_dur == "10"){echo "selected=\"selected\"";} ?> value="10">10</option>
            <option <?php if(isset($video_dur) && $video_dur == "15"){echo "selected=\"selected\"";} ?> value="15">15</option>
            <option <?php if(isset($video_dur) && $video_dur == "20"){echo "selected=\"selected\"";} ?> value="20">20</option>
            <option <?php if(isset($video_dur) && $video_dur == "30"){echo "selected=\"selected\"";} ?> value="30">30</option>
            <option <?php if(isset($video_dur) && $video_dur == "50"){echo "selected=\"selected\"";} ?> value="50">50</option>
            <option <?php if(isset($video_dur) && $video_dur == "60"){echo "selected=\"selected\"";} ?> value="60">60</option>
            </select>
            <p></p>
            Number of video's: <select name = "num_video" id = "num_video">
            <option <?php if(isset($num_video) && $num_video == "9"){echo "selected=\"selected\"";} ?> value="9">9</option>
            <option <?php if(isset($num_video) && $num_video == "8"){echo "selected=\"selected\"";} ?> value="8">8</option>
            <option <?php if(isset($num_video) && $num_video == "7"){echo "selected=\"selected\"";} ?> value="7">7</option>
            <option <?php if(isset($num_video) && $num_video == "6"){echo "selected=\"selected\"";} ?> value="6">6</option>
            <option <?php if(isset($num_video) && $num_video == "5"){echo "selected=\"selected\"";} ?> value="5">5</option>
            <option <?php if(isset($num_video) && $num_video == "4"){echo "selected=\"selected\"";} ?> value="4">4</option>
            <option <?php if(isset($num_video) && $num_video == "3"){echo "selected=\"selected\"";} ?> value="3">3</option>
            <option <?php if(isset($num_video) && $num_video == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
            <option <?php if(isset($num_video) && $num_video == "1"){echo "selected=\"selected\"";} ?> value="1">1</option>
            </select>
        </fieldset>
    </div>
    <br><p></p>
    <div id="submit" align="center"></div>
    <div class="w3" align="center">
    <br>
    <button type="submit">Submit</button>
</form>
</div>     

<!-- Here is our page's main content -->
<main>
    <br>
    <div id="result" align="center"></div>
    <div class="w3" align="center">
    <br>
    <h5> <a href="/index.php">  Resultat sida  </a></h5>
    </div>
</main>
</body>
</html>
