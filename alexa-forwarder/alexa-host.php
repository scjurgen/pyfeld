<?php

/*
connect to alexa forwarder 
(http request on localhost)
*/

#posix_mkfifo("/tmp/alexa/fifo",0644);

function get_request()
{
    return file_get_contents('php://input');
}

function getRequestHeaders()
{
    $headers = array();
    foreach ($_SERVER as $key => $value) {
        if (substr($key, 0, 5) <> 'HTTP_') {
            continue;
        }
        $header = str_replace(' ', '-', ucwords(str_replace('_', ' ', strtolower(substr($key, 5)))));
        $headers[$header] = $value;
    }
    return $headers;
}

function log_data($msg)
{
    $log_fp = fopen("/tmp/alexa/requests.log", "a");
    fwrite($log_fp, $msg);
    fclose($log_fp);
}

function log_request()
{
    global $request_body;
    $headers = getRequestHeaders();
    $result = "\n#new request ". date("Ymd His");
    foreach ($headers as $header => $value) {
        $result.= "\n\t$header: $value";
    }
    log_data($result);
}

function pipe_request($msg)
{
    $pipe = fopen("/tmp/alexa/fifo", "a");
    fwrite($pipe, $msg."\n");
    fclose($pipe);
}

function forwarder_request($msg)
{
    $response = file_get_contents('http://62.75.216.162:24443/'.$msg);
    if ($response === FALSE)
    {
        $error = error_get_last();
        log_data("\n#response ".$error['message']);
        return "Ein Fehler ist aufgetreten: Ist Raum-feld verbunden?";
    }
    log_data("\n#response ".$response);
    return $response;
}

$unknown_response_template = '{
  "version": "1.0",
  "response": {
    "outputSpeech": {
      "type": "PlainText",
      "text": "Huh?"
    },
    "shouldEndSession": true
  }
}';


$play_response_template = '{
  "version": "1.0",
  "response": {
    "outputSpeech": {
      "type": "PlainText",
      "text": "#response#"
    },
    "shouldEndSession": true
  }
}';


$search_response_template = '{
  "version": "1.0",
  "response": {
    "outputSpeech": {
      "type": "PlainText",
      "text": "#response#"
    },
    "shouldEndSession": true
  }
}';

$room_response_template = '{
  "version": "1.0",
  "response": {
    "outputSpeech": {
      "type": "PlainText",
      "text": "#response#"
    },
    "shouldEndSession": true
  }
}';

$action_response_template = '{
  "version": "1.0",
  "response": {
    "outputSpeech": {
      "type": "PlainText",
      "text": "#response#"
    },
    "shouldEndSession": true
  }
}';
$request_body = get_request();

log_request();
log_data($request_body);

$json = json_decode($request_body);
$user_id = $json->{'session'}->{'user'}->{'userId'};

$application_id = $json->{'session'}->{'application'}->{'applicationId'};

if ($application_id != "amzn1.ask.skill.06ef7c46-1134-4fdc-bd67-a85792dac97a" &&
    $application_id != "amzn1.ask.skill.af6b0afe-e5a2-4a67-92c5-04ca1879386c")
{
    http_response_code(403);
    return;
}

function get_slot_value($slots, $name)
{
    return $slots->{$name}->{'value'};
}


if ($json->{'request'}->{"type"} == "IntentRequest")
{
    $intent = $json->{'request'}->{"intent"};
    if ($intent->{'name'} == 'PlayAt') {
        $slots = $intent->{'slots'};
        $itemNumber = (int)get_slot_value($slots,'itemnumber');
        $itemNumber -= 1;
        $context = get_slot_value($slots,'context');
        $atTime =  get_slot_value($slots,'time');
        #print("play ".$context." ".$itemNumber);
        pipe_request($user_id." play ".$context." ".$itemNumber);
        $result = forwarder_request($user_id."/playat/".$atTime."/".$context."/".$itemNumber);
        $response_template = str_replace("#response#", $result, $play_response_template);
    }
    if ($intent->{'name'} == 'PlaySomething') {
        $slots = $intent->{'slots'};
        $itemNumber = (int)get_slot_value($slots,'itemnumber');
        $itemNumber -= 1;
        $context = get_slot_value($slots,'context');
        #print("play ".$context." ".$itemNumber);
        pipe_request($user_id." play ".$context." ".$itemNumber);
        $result = forwarder_request($user_id."/play/".$context."/".$itemNumber);
        $response_template = str_replace("#response#", $result, $play_response_template);
    }
    if ($intent->{'name'} == 'SetRoom') {
        $slots = $intent->{'slots'};
        $room = get_slot_value($slots,'rooms');
        pipe_request($user_id." room ".$room);
        $result = forwarder_request($user_id."/room/".$room);
        $response_template = str_replace("#response#", $result, $room_response_template);
    }
    if ($intent->{'name'} == 'GeneralAction') {
        $slots = $intent->{'slots'};
        $action = get_slot_value($slots,'action');
        pipe_request($user_id." action ".$action);
        $result = forwarder_request($user_id."/action/".$action);
        $response_template = str_replace("#response#", $result, $action_response_template);
    }
}

echo $response_template;
?>