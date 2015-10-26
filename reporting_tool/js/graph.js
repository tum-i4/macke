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
  createGraph();
}

$(document).ready(function() {
  // Fill the current width and height of graph in Width-Height form
  $("#canvasWidth").val($("#graph").width());
  $("#canvasHeight").val($("#graph").height());
  
  colorNodes();
  createGraph();
});

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
        gravitationalConstant: -60000,
        springConstant: 0.02
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