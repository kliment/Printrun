(function() {
  var $console;

  var windowFocus = true;

  $(window).focus(function() {
      windowFocus = true;
      //if ($console) $console.append("Window refocused, restarting graph.\n");
      $(".focus-lost-overlay").addClass("out").removeClass("in").delay(1000).hide();
  }).blur(function() {
      windowFocus = false;
      //if ($console) $console.append("Window's focus, lost stopping graph...\n");
      $(".focus-lost-overlay")
        .stop(true,true)
        .show()
        .addClass("in")
        .removeClass("out");
  }.debounce());

  var connect = function() {
    // Let us open a web socket
    var hostname = window.location.hostname;
    var url = "ws://"+hostname+":8888/socket?user=admin&password=admin";
    console.log(url);
    var ws = new WebSocket(url, "construct.text.0.2");
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
  }

  var onConnect = function(ws) {
    ws.onopen = function()
    {
      $console.append("Connected.\n");
      // Web Socket is connected, send data using send()

    };
    var nextGraphPoint = {};
    ws.onmessage = function (evt) 
    {
      msg = JSON.parse(evt.data)
      if(msg.sensor_changed != undefined)
      {
        var sensorNames = ["bed", "extruder"];
        for (var i = 0; i < sensorNames.length; i++)
        {
          var name = msg.sensor_changed.name;
          var val = parseFloat(msg.sensor_changed.value);
          nextGraphPoint[name] = val;
          $("."+name+" .val").data("val", val.format(1))
        }
        if(nextGraphPoint.bed != undefined && nextGraphPoint.extruder != undefined)
        {
          nextGraphPoint.timestamp = msg.timestamp
          updateGraphData(nextGraphPoint);
          nextGraphPoint = {};
        }
        requestAnimationFrame(updateUi);
      }
      else if (msg.job_progress_changed != undefined)
      {
        val = Math.round(parseFloat(msg.job_progress_changed)*10)/10;
        $(".job-pogress .val").html(val);
      }
      else
      {
        console.log($consoleWrapper.scrollTop() - $console.innerHeight())
        var atBottom = $consoleWrapper.scrollTop() - $console.innerHeight() > -220;
        $console.append(evt.data + "\n");
        if (atBottom)
        {
          $consoleWrapper.scrollTop($console.innerHeight());
        }
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