console.log("w00t!");

var $console;

var connect = function() {
  // Let us open a web socket
  var url = "ws://localhost:8888/socket?user=admin&password=admin";
  console.log(url);
  var ws = new WebSocket(url);
  $(function () {
    $consoleWrapper = $(".console");
    $console = $(".console pre");
    $console.html("Connecting...")
    onConnect(ws)
  });
};

var onConnect = function(ws) {
  ws.onopen = function()
  {
    $console.append("\nConnected."); 
    // Web Socket is connected, send data using send()

  };
  ws.onmessage = function (evt) 
  {
    msg = JSON.parse(evt.data)
    if(msg.sensors != undefined)
    {
      var sensorNames = ["bed", "extruder"];
      for (var i = 0; i < sensorNames.length; i++)
      {
        var name = sensorNames[i];
        var val = parseFloat(msg.sensors[name]);
        $("."+name+" .val").html(val.format(1));
      }
    }
    $console.append("\n"+evt.data);
    $consoleWrapper.scrollTop($console.innerHeight());
  };
  ws.onclose = function()
  { 
    // websocket is closed.
    $console.append("\nConnection closed."); 
  };
};

if ("WebSocket" in window)
{
  connect();
}
else
{
   // The browser doesn't support WebSocket
   alert("Error: WebSocket NOT supported by your Browser!");
}