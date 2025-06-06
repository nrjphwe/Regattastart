<?php
    define('APP_VERSION', '2025.05.20'); // You can replace '1.0.0' with your desired version number
    // Start the session
    ini_set('session.gc_maxlifetime', 86400); // 24 hours
    session_set_cookie_params(86400); // 24 hours
    if (session_status() === PHP_SESSION_NONE) {
        session_id("regattastart");
        session_start();
    }
    ini_set('display_errors', 1);
    error_reporting(E_ALL);
    // Check if the session is already started
    print_r($_SESSION);
    echo "<br/>";
    print_r($_POST);
    echo "<br/>";
?>
<?php
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Process and store the form data
        $_SESSION["form_data"] = $_POST;

        // Execute the Python script
        $command = 'python3 /usr/lib/cgi-bin/regattastart6.py ' . escapeshellarg(json_encode($_POST)) . ' > /var/www/html/output.txt 2>&1 &';
        shell_exec($command);
        echo date('h:i:s') . "<br>";
        echo "execution started";
        sleep(3);

        // Redirect to index.php
        header("Location: index.php");
        exit;
    }
    $day = date("l");
    $start_time = "18:25"; // You need to initialize $start_time
    $video_delay = isset($_SESSION["form_data"]["video_delay"]) ? $_SESSION["form_data"]["video_delay"] : "";
    $video_dur = isset($_SESSION["form_data"]["video_dur"]) ? $_SESSION["form_data"]["video_dur"] : "";
    $num_video = isset($_SESSION["form_data"]["num_video"]) ? $_SESSION["form_data"]["num_video"] : "";
    $num_starts = isset($_SESSION["form_data"]["num_starts"]) ? $_SESSION["form_data"]["num_starts"] : "";
    $dur_between_starts = isset($_SESSION["form_data"]["dur_between_starts"]) ? $_SESSION["form_data"]["dur_between_starts"] : "";
?>
<!DOCTYPE html>
<html>
<head>
    <title> Regattastart6 för setup av en eller 2 starter </title> 
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/w3.css">
    <!-- set styles -->
    <style>
        /* Center align the content */
        .content-wrapper {
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }
        /* Ensure the form fields are displayed in a row */
        .w3-row-padding {
            display: flex;
            flex-wrap: wrap; /* Allow wrapping of elements */
            justify-content: space-around; /* Align elements evenly horizontally */
        }
        /* Style for individual form field containers */
        .w3-container {
            flex: 1; /* Let each container take up equal space */
            margin-bottom: 10px; /* Add some bottom margin for spacing between rows */
        }

        /* Adjust the width of the columns for smaller screens */
        @media screen and (max-width: 600px) {
            .w3-half {
                width: 100%; /* Make each column take up full width on smaller screens */
            }
        }
    </style>
</head>
<body>
<header>
    <div style="text-align: center;" class="w3-container w3-blue">
        <h2>Regattastart6 for 1 or 2 starts </h2>
    </div>
    <div style="text-align: center;">
        <?php echo "     Version: " . APP_VERSION . "<p></p>"; ?>
    </div>
</header>
<!-- HTML form -->
<div class="w3-container" style="text-align: center;">
    <!-- Content Wrapper with center alignment -->
    <div class="w3-margin w3-padding-large content-wrapper">
        <form action="index6.php" method="POST">
            <div class="w3-row-padding">
                <!-- Left side content -->
                <div class="w3-half">
                    <div class="w3-pale-yellow" style="text-align: center;">
                        <fieldset>
                            <legend>Day and time setup: </legend>
                            <?php $day = date("l") ?>
                            <br>
                            Day for race <select name = "day" id="day">
                                <option <?php if(isset($day) && $day == "Monday"){echo "selected=\"selected\"";} ?> value="Monday">Monday</option>
                                <option <?php if(isset($day) && $day == "Tuesday"){echo "selected=\"selected\"";} ?> value="Tuesday">Tuesday</option>
                                <option <?php if(isset($day) && $day == "Wednesday"){echo "selected=\"selected\"";} ?> value="Wednesday">Wednesday</option>
                                <option <?php if(isset($day) && $day == "Thursday"){echo "selected=\"selected\"";} ?> value="Thursday">Thursday</option>
                                <option <?php if(isset($day) && $day == "Friday"){echo "selected=\"selected\"";} ?> value="Friday">Friday</option>
                                <option <?php if(isset($day) && $day == "Saturday"){echo "selected=\"selected\"";} ?> value="Saturday">Saturday</option>
                                <option <?php if(isset($day) && $day == "Sunday"){echo "selected=\"selected\"";} ?> value="Sunday">Sunday</option>
                            </select>
                            <p></p>
                            <div data-tap-disabled="true">
                            <?php
                                // Set the correct time zone (adjust as needed)
                                date_default_timezone_set('Europe/Stockholm'); //your time zone

                                $start_time = isset($_SESSION["form_data"]["start_time"]) ? $_SESSION["form_data"]["start_time"] : "";
                                $steps = 5; // Set to 10, for test set to 5, You can adjust the value of $steps according to your needs
                                $loops = 24 * (60 / $steps); // Define $loops here or wherever it makes sense in your code
                                
                                // Get the current time in seconds since the Unix Epoch
                                $current = time(); 
                                $adjusted_time = $current + (5 * 60);

                                // Calculate the nearest time in 5-minute intervals
                                $nearest_time = strtotime('today') + ceil(($adjusted_time - strtotime('today')) / (5 * 60)) * (5 * 60);

                                // Format the pre-selected option
                                $start_time_option = date('H:i', $nearest_time);
                            ?>
                            Start Time: <select name="start_time" id="start_time">
                                <?php
                                    for ($i = 0; $i < $loops; $i++) {
                                         // Calculate the time for this option
                                        $time_option = date('H:i', $nearest_time + ($i * $steps * 60));
                                        // Check if this option should be selected
                                        $selected = ($time_option == $start_time_option) ? "selected" : ""; 
                                        // Output the option tag
                                        echo '<option value="' . $time_option . '" ' . $selected . '>' . $time_option . '</option>';
                                    }
                                ?>
                            </select>
                            <br>
                            <p style="font-size:11px">
                            (First start in case of 2 starts)
                            <br>
                        </fieldset>
                    </div>
                </div>
                <!-- Right side content -->
                <div class="w3-half">
                    <div class="w3-pale-yellow" style="text-align: center;">
                        <fieldset>
                            <legend>Video Setup: </legend>
                            <p></p>
                            Duration between start and estimated finish: 
                            <select name = "video_delay" id = "video_delay">
                                <option value="20" <?php if(isset($video_delay) && $video_delay == "20"){echo "selected=\"selected\"";} ?>>20</option>
                                <option value="30" <?php if(isset($video_delay) && $video_delay == "30"){echo "selected=\"selected\"";} ?>>30</option>
                                <option value="40" <?php if(isset($video_delay) && $video_delay == "40"){echo "selected=\"selected\"";} ?>>40</option>
                                <option value="50" <?php if(isset($video_delay) && $video_delay == "50"){echo "selected=\"selected\"";} ?>>50</option>
                                <option value="60" <?php if(isset($video_delay) && $video_delay == "60"){echo "selected=\"selected\"";} ?>>60</option>
                                <option value="70" <?php if(isset($video_delay) && $video_delay == "70"){echo "selected=\"selected\"";} ?>>70</option>
                                <option value="80" <?php if(isset($video_delay) && $video_delay == "80"){echo "selected=\"selected\"";} ?>>80</option>
                                <option value="5" <?php if(isset($video_delay) && $video_delay == "5"){echo "selected=\"selected\"";}  ?>>5</option>
                            </select>
                            <p></p>
                            Duration for each video: 
                            <select name = "video_dur" id = "video_dur">
                                <option value="10" <?php if(isset($video_dur) && $video_dur == "10"){echo "selected=\"selected\"";} ?> value="10">10</option>
                                <option value="15" <?php if(isset($video_dur) && $video_dur == "15"){echo "selected=\"selected\"";} ?> value="15">15</option>
                                <option value="20" <?php if(isset($video_dur) && $video_dur == "20"){echo "selected=\"selected\"";} ?> value="20">20</option>
                                <option value="30" <?php if(isset($video_dur) && $video_dur == "30"){echo "selected=\"selected\"";} ?> value="30">30</option>
                                <option value="50" <?php if(isset($video_dur) && $video_dur == "50"){echo "selected=\"selected\"";} ?> value="50">50</option>
                                <option value="60" <?php if(isset($video_dur) && $video_dur == "60"){echo "selected=\"selected\"";} ?> value="60">60</option>
                                <option value="2"  <?php if(isset($video_dur) && $video_dur == "2"){echo "selected=\"selected\"";} ?> value="2">2</option> 
                            </select>
                            <p></p>
                            Number of video's: 
                            <select name = "num_video" id = "num_video">
                                <option <?php if(isset($num_video) && $num_video == "9"){echo "selected=\"selected\"";} ?> value="9">9</option>
                                <option <?php if(isset($num_video) && $num_video == "8"){echo "selected=\"selected\"";} ?> value="8">8</option>
                                <option <?php if(isset($num_video) && $num_video == "7"){echo "selected=\"selected\"";} ?> value="7">7</option>
                                <option <?php if(isset($num_video) && $num_video == "6"){echo "selected=\"selected\"";} ?> value="6">6</option>
                                <option <?php if(isset($num_video) && $num_video == "5"){echo "selected=\"selected\"";} ?> value="5">5</option>
                                <option <?php if(isset($num_video) && $num_video == "4"){echo "selected=\"selected\"";} ?> value="4">4</option>
                                <option <?php if(isset($num_video) && $num_video == "3"){echo "selected=\"selected\"";} ?> value="3">3</option>
                                <option <?php if(isset($num_video) && $num_video == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
                            </select>
                        </fieldset>
                    </div>
                </div>
            </div>
            <br>
            <!-- central content below pale-yellow -->
            <div class="w3-row-padding">
                <div class="w3-round w3-light-grey w3-cell">
                    <fieldset>
                        <legend> Setup of 1 or 2 starts </legend>
                        <p></p>
                        Number of starts: <select name="num_starts" id="num_starts">
                            <option <?php if(isset($num_starts) && $num_starts == "1"){echo "selected=\"selected\"";} ?> value="1">1</option>
                            <option <?php if(isset($num_starts) && $num_starts == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
                        </select>
                        <p></p>
                        <!-- Option that should be hidden when only one start -->
                        <div id="secondOptionContainer" style="display: none;">
                            <span id="secondOptionText">In case of 2 starts, duration between the starts:</span>
                            <select name="dur_between_starts" id="dur_between_starts">
                                <option <?php if(isset($dur_between_starts) && $dur_between_starts == "5"){echo "selected=\"selected\"";} ?> value="5">5</option>
                                <option <?php if(isset($dur_between_starts) && $dur_between_starts == "10"){echo "selected=\"selected\"";} ?> value="10">10</option>
                            </select>
                        </div>
                    </fieldset>
                </div>
            </div>
            <div>
                <p>
            </div>
            <!-- Execute button, central below ligth-grey -->
            <div class="w3-row-padding">
                <div class="w3-round w3-blue w3-cell">
                    <fieldset>
                        <legend>Execute</legend>
                        <div id="submit" align="center"></div>
                            <div class="w3" align="center">
                                <button type="submit">Submit</button>
                            </div>
                    </fieldset>
                </div>
            </div>
        </form>
     </div>
</div>
<!-- Here is our page's main content -->
<main>
    <div id="result" align="center"></div>
        <div class="w3-container" align="center">
        <div class="w3-row-padding" style="text-align: center;">
            <div id="result" ></div>
        </div>
    <h5><a href="/index.php">  Resultat sida  </a></h5>
</main>
<footer>
    <div style="text-align: center;" class="w3-panel w3-grey">
        <?php
            // output when index6.php was last modified.
            $filename = 'index6.php';
            if (file_exists($filename)) {
                echo "This web-page: $filename was last modified: " . date ("Y-m-d H:i:s.", filemtime($filename));
            }
        ?>
    </div>
    <div class="w3-row-padding" align="center">
        <br><p> - phwe - <br></p>
    </div>
</footer>
<!-- JavaScript to show/hide the second option based on the condition 1 or 2 starts -->
<script>
    // JavaScript to show/hide the second option based on the condition 1 or 2 starts
    document.addEventListener('DOMContentLoaded', function() {
        var numStarts = <?php echo json_encode($num_starts); ?>;
        var secondOptionContainer = document.getElementById('secondOptionContainer');
        toggleSecondOption(numStarts, secondOptionContainer);

        document.querySelector('select[name="num_starts"]').addEventListener('change', function(event) {
            var selectedValue = event.target.value;
            toggleSecondOption(selectedValue, secondOptionContainer);
        });
    });

    function toggleSecondOption(numStarts, containerElement) {
        if (numStarts == 2) {
            containerElement.style.display = 'block';
        } else {
            containerElement.style.display = 'none';
        }
    }
</script>
</body>
</html>
