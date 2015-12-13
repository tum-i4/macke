// Function to convert graph into pdf - Not working properly with big dimention. Will update soon.
function convertToPdf() {
  var pdfWidth = Math.round(($("#graph").width()) * 0.264583333);
  var pdfHeight = Math.round(($("#graph").height()) * 0.264583333);
  return xepOnline.Formatter.Format('graph', {
    pageWidth: pdfWidth + 'mm',
    pageHeight: pdfHeight + 'mm',
    render: 'download',
    pageMargin: '0in',
    resolution: 100
  });
}

// Function to change the dimentions of the graph
function changeDimention() {
  $("#graph").html('');
  $("#graph").width($("#canvasWidth").val());
  $("#graph").height($("#canvasHeight").val());
  $("#graphContainer").scrollTop($("#graph").height()/2-200);
  $("#graphContainer").scrollLeft($("#graph").width()/2-500);
  createGraph();
}

$(document).ready(function() {
  // Fill the current width and height of graph in Width-Height form
  $("#canvasWidth").val($("#graph").width());
  $("#canvasHeight").val($("#graph").height());
  $("#graphContainer").scrollTop($("#graph").height()/2-200);
  var default_L = 3;
  var default_I = 5;
  var default_N = 2;
  var default_D = 4;
  var default_O = 1;
  $('#L').val(default_L);
  $('#I').val(default_I);
  $('#N').val(default_N);
  $('#D').val(default_D);
  $('#O').val(default_O);
  calculateSeverity(default_L, default_I, default_N, default_D, default_O);
  colorNodes();
  createGraph();
});

// Function to change severity when new L, I, N, D, O are specified
function changeSeverity(){
  $("#graph").html('');
  var new_L = $('#L').val();
  var new_I = $('#I').val();
  var new_N = $('#N').val();
  var new_D = $('#D').val();
  var new_O = $('#O').val();
  calculateSeverity(new_L, new_I, new_N, new_D, new_O);
  colorNodes();
  createGraph();
}

// calculates severity as severity = L*factor_L + I*factor_I + N*factor_N + D*factor_D + O*factor_O
function calculateSeverity(L, I, N, D, O){
  for (var i = 0; i < nodesJSON.length; i++) {
    nodesJSON[i].severity = (L*nodesJSON[i].factor_L) + (I*nodesJSON[i].factor_I) + (N*nodesJSON[i].factor_N) + (D*nodesJSON[i].factor_D) + (O*nodesJSON[i].factor_O);
  }
}

// change color according to severity
function colorNodes() {
  for (var i = 0; i < nodesJSON.length; i++) {
    if (nodesJSON[i].severity >= 0 && nodesJSON[i].severity < 11) {
      // GrayScale nodesJSON[i].color="#D9D9D9";
      nodesJSON[i].color = "#FFFF00";
      // Overriding font color for light backgound nodes
      nodesJSON[i].fontColor = "black";
    } else if (nodesJSON[i].severity > 10 && nodesJSON[i].severity < 21) {
      // GrayScale nodesJSON[i].color="#8A8A8A";
      nodesJSON[i].color = "#FFAA00";
      nodesJSON[i].fontColor = "black"; // Not for GrayScale
    } else if (nodesJSON[i].severity > 20 && nodesJSON[i].severity < 41) {
      // GrayScale nodesJSON[i].color="#555555";
      nodesJSON[i].color = "#FF5500";
    } else if (nodesJSON[i].severity > 40) {
      // GrayScale nodesJSON[i].color="#000000";
      nodesJSON[i].color = "#CC0000";
    } else {
      console.log("Severity cannot be less than 0 for Node " + i);
    }
  }
}

// Creates graph
function createGraph() {
  var container = document.getElementById('graph');
  var data = {
    nodes: nodesJSON,
    edges: edgesJSON
  };
  var options = {
    tooltip: {
      delay: 50,
      fontColor: "white",
      fontSize: 14,
      fontFace: "verdana",
      color: {
        border: "white",
        background: "#FFFFC6"
      }
    },
    clustering: {
      enabled: false,
      clusterEdgeThreshold: 50
    },
    physics: {
      enabled: false,
      barnesHut: {
        gravitationalConstant: -5000,
        springConstant: 0.001
      }
    },
    smoothCurves: {
      dynamic: false
    },
    hideEdgesOnDrag: true,
    stabilize: true,
    stabilizationIterations: 1000,
    zoomExtentOnStabilize: true,
    nodes: {
      fontColor: "white",
      borderWidth: 2,
      shadow: true
    },
    edges: {
      style: "arrow",
      width: 1
    }
  };
  var network = new vis.Network(container, data, options);

  // Method to change nodes to hyperlink
  network.on('click', function(properties) {
    if (properties.nodes.length != 0) {
      nodesJSON.filter(function(node) {
        if (node.id == properties.nodes[0]) {
          window.location = "./html/" + node.label + ".html";
        }
      });
    }
  });
}