<?php
$pronterfaceIP = "192.168.0.102:8080"; //Format: ip:port

$curl = curl_init();
curl_setopt($curl, CURLINFO_HEADER_OUT, true);
curl_setopt($curl, CURLOPT_HEADER, false);
curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
curl_setopt($curl, CURLOPT_CONNECTTIMEOUT, 1);
curl_setopt($curl,CURLOPT_TIMEOUT, 1);
curl_setopt($curl, CURLOPT_URL, "http://" . $pronterfaceIP . "/status/");
$data = curl_exec($curl);

if (curl_errno($curl) || empty($data))
{
	die("Printer offline");
}

curl_close($curl);

try
{
	$xml = new SimpleXMLElement($data);	
	echo "State: " . $xml->state . "<br />";
	echo "Hotend: " . round($xml->hotend, 0) . "&deg;c<br />";
	echo "Bed: " . round($xml->bed, 0) . "&deg;c<br />";
	if ($xml->progress != "NA")
	{
		echo "Progress: " . $xml->progress . "%";
	}
}
catch(Exception $e)
{
	echo "ERROR:\n" . $e->getMessage(). " (severity " . $e->getCode() . ")";
}
?>