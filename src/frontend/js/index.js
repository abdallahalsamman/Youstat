$('document').ready(function(){
    $('#btn_submit').click(function(e){
        user_input = $('#input_channel')[0].value;
        $("#result")[0].innerHTML = "Loading...";
        $.get({
            'url': '/api/'+user_input,
            success: function(data){
                words_count = JSON.parse(data);
                html = "<br><br>";
                html += "<table border='1px' >";
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
