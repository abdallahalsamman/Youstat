$('document').ready(function(){
    $('#btn_submit').click(function(e){
        channel_name = $('#input_channel')[0].value;
        $("#result")[0].innerHTML = "Loading...";
        $.get({
            'url': '/api/channel/'+channel_name,
            success: function(data){
                words_count = JSON.parse(data);
                html = "<table border='1px' >";
                words_count.forEach(function(word){
                    html += "<tr><td>" + word[0] + "</td>";
                    html += "<td>" + word[1] + "</td></tr>";
                });
                html += "</table>";
                $("#result")[0].innerHTML = html;
            }
        })
    })
})
