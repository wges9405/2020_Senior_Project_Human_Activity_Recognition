
var info_circle = $('#info-circle-card')

info_circle.circleProgress({
  value: 0,
});

function Update_circleProgress (Array) {
  info_circle.circleProgress({
    value: 1,
    fill: { gradient: [["green", Array[0]/100], ["red", Array[0]/100]]},
    animation: {duration:1}
  });

};

/*   Dynamic change data
$('#connection').click(function() {
	info_circle.circleProgress({
    value:1,
  fill: { gradient: [["green", parseInt( $('#static').text() )/100], ["red", parseInt( $('#static').text() )/100]]}
  })
})
*/

/*
$( function () {
    "use strict";

    // Info circle card
    $('#info-circle-card').circleProgress({
        value: parseInt( $('#static').text() )/100,
        fill: {color: "#28a745"},
        emptyFill: "#dc3545",
    } );
} );
*/