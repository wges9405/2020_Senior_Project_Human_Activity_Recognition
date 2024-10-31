// Connetion w/ python

if ($('a#connection').text().trim()=='Disconnected') {
    $('a#connection').on('click', function () {
        $.getJSON('/connecting_device', function (status) {
            console.log(status)
            $('#connection').text(status)
            $.getJSON('/predict_process', function (str) {
                console.log(str)
            })
        })

        var sitv = setInterval( function () {
            $.getJSON('/show_progress', function (Array) {
                console.log(Array)
                $('#static').text(Array[0])
                $('#dynamic').text(Array[1])
                Update_circleProgress(Array.slice(0,2))
                Update_morris_bar(Array.slice(2))

                document.getElementById("GIF").className = getActivity(Array.slice(2))
            })
        }, 2560)

        //document.getElementById("GIF").className = 'div2'
    })
}

function getActivity(array) {
    const activity = ["center nothing", "center sit_stand", "center lay", "center walk", "center upstair", "center downstair"];
    if (array[argMax(array)]==0)
	return activity[0]
    else
        return activity[argMax(array)+1]
}
function argMax(array) {
    return array.map((x, i) => [x, i]).reduce((r, a) => (a[0] > r[0] ? a : r))[1];
}


/*
範例
$('.btn').on('click', function () {
    console.log("come in ")
    var log = ""
    var sitv = setInterval( function() {
        var prog_url = '/show_progress'              // prog_url指请求进度的url，后面会在django中设置
        $.getJSON(prog_url, function(num_progress) {


            {# console.log("come in num_progress="+num_progress) #}
            log = log + num_progress+ "-"
            $('.progress-div').css('visibility', 'visible');
            $('.progress-bar').css('width', num_progress + '%');
            $('.progress-bar').text(num_progress + '%');
            $('.progress-text').text( '显示日志'+log );
            $('.progress-text').css('width', '100%');

            {# $('#prog_in').width(res + '%'); #}
            if(num_progress == '99'){
                console.log("come in 99")
                clearInterval(sitv);
                $('.progress-bar').css('width', '100%');
                $('.progress-bar').text('100%');
            }

        });
    }, 10);                                 // 每10毫秒查询一次后台进度


    var thisurl = '/process_data'                      // 指当前页面的url
    {# var yourjson = '90' #}
    $.getJSON(thisurl, function(res){
        console.log("sitv over res"+res)
        clearInterval(sitv);                   // 此时请求成功返回结果了，结束对后台进度的查询
    });

})*/
