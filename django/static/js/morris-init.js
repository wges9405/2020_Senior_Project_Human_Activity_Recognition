var morris_bar = Morris.Bar( {
	element: 'morris-bar-chart',
	data: [ {
		Activity: 'Sit / Stand',
		a: 0.0,
	}, {
		Activity: 'lay',
		a: 0.0,
	},{
		Activity: 'Walk',
		a: 0.0,
	}, {
		Activity: 'Upstair',
		a: 0.0,
	}, {
		Activity: 'Downstair',
		a: 0.0,
	} ],
	xkey: 'Activity',
	ykeys: [ 'a' ],
	labels: [ 'Probability' ],
	barColors: [ '#0b62a4' ],
	gridLineColor: "#777",
	hideHover: true,
	resize: true,
	ymax: 1,
	ymin: 0,
} );


function Update_morris_bar (Array) {
    morris_bar.setData(
		[{
			Activity: 'Sit / Stand',
			a: Array[0],
		}, {
			Activity: 'lay',
			a: Array[1],
		},{
			Activity: 'Walk',
			a: Array[2],
		}, {
			Activity: 'Upstair',
			a: Array[3],
		}, {
			Activity: 'Downstair',
			a: Array[4],
		} ]
	)
};