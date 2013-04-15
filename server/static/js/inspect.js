(function() {
  var $console;

  var windowFocus = true;

  $(window).focus(function() {
      windowFocus = true;
      if ($console) $console.append("Window refocused, restarting log.\n");
      $(".focus-lost-overlay").addClass("out").removeClass("in");
  }).blur(function() {
      windowFocus = false;
      if ($console) $console.append("Window's focus, lost stopping logging...\n");
      $(".focus-lost-overlay").addClass("in").removeClass("out");
  }.debounce());

  var connect = function() {
    // Let us open a web socket
    var url = "ws://localhost:8888/socket?user=admin&password=admin";
    console.log(url);
    var ws = new WebSocket(url);
    $(function () {
      $consoleWrapper = $(".console");
      $console = $(".console pre");
      $console.html("Connecting...\n")
      onConnect(ws)
    });
  };

  var updateSensorsUi = function() {
    $(".sensors .val").each(function() {
      $(this).html($(this).data("val")||"xx.x");
    })
  }.throttle(800);

  var graph = null;
  var graphData = [];
  var graphResolution = 40;

  var updateGraphData = function(current) {
    current.time = Date.now();
    if(graphData.length == graphResolution) graphData.shift();
    graphData.push(current);
  }

  var updateGraphUi = function(current) {
    if(graph == null)
    {
      graph = new Morris.Line({
        // ID of the element in which to draw the chart.
        element: "temperature-graph",
        // Chart data records -- each entry in this array corresponds to a point on
        // the chart.
        data: graphData,
        // The name of the data record attribute that contains x-values.
        xkey: 'timestamp',
        // A list of names of data record attributes that contain y-values.
        ykeys: ['extruder', 'bed'],
        // Labels for the ykeys -- will be displayed when you hover over the
        // chart.
        labels: ['extruder &deg;C', 'bed &deg;C'],
        hideHover: 'always',
        ymax: 'auto 250',
        //pointSize: 0,
        //parseTime: false,
        xLabels: "decade"
      });
    }
    else
    {
      graph.setData(graphData);
    }
  }

  var updateUi = function(msg) {
    if(windowFocus == false) return;
    updateSensorsUi();
    updateGraphUi();
    $console.append($console.data("toBeWritten"));
    $console.data("toBeWritten", "");
    $consoleWrapper.scrollTop($console.innerHeight());
  }

  var onConnect = function(ws) {
    ws.onopen = function()
    {
      $console.append("Connected.\n");
      // Web Socket is connected, send data using send()

    };
    ws.onmessage = function (evt) 
    {
      msg = JSON.parse(evt.data)
      if(msg.sensors != undefined)
      {
        var sensorNames = ["bed", "extruder"];
        var values = {timestamp: msg.timestamp};
        for (var i = 0; i < sensorNames.length; i++)
        {
          var name = sensorNames[i];
          var val = parseFloat(msg.sensors[name]);
          values[name] = val;
          $("."+name+" .val").data("val", val.format(1))
        }
        if(windowFocus)
        {
          var previous = $console.data("toBeWritten") || "";
          $console.data("toBeWritten", previous + evt.data + "\n");
        }
        updateGraphData(values);
        requestAnimationFrame(updateUi);
      }
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
})();