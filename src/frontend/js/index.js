$('document').ready(function(){

    var render_frequent_words = function(data){
        words_count = JSON.parse(data);
        html = "<br><br>";
        html += "<table border='1px' >";
        words_count.forEach(function(word){
            html += "<tr><td>" + word[0] + "</td>";
            html += "<td>" + word[1] + "</td></tr>";
        });
        html += "</table>";
        $("#result")[0].innerHTML = html;
    };

    var submit = function(e){
        user_input = $('#input_channel')[0].value;
        $("#result")[0].innerHTML = "Loading...";
        var xhr = new XMLHttpRequest()
        xhr.open("GET", "/api?url="+encodeURIComponent(user_input)+"&accurate="+ (e.target.id == "btn_accurate" ? "true" : "false"), true)
        xhr.onprogress = function () {
          percentages = xhr.responseText.replace(/\s/g,"").split("%")
          last_percentage = percentages[percentages.length-1]
          if(last_percentage){
            render_frequent_words(last_percentage)
          }else{
            $("#result")[0].innerHTML = percentages[percentages.length-2]+"%"
          }
        }
        xhr.send()
        /*$.get({
            url: '/api'
            , data: {
                url: user_input
                , accurate: e.target.id == "btn_accurate"
            }
            , success: render_frequent_words
        });*/
    };

    $('#btn_submit').click(submit);
    $("#input_channel").keyup(function(e){
      if(e.keyCode == 13){
        submit(e);
      }
    });
    $('#btn_accurate').click(submit);
    $('#input_channel').bind("enterKey", submit);

})
