$('document').ready(function(){

    var render_frequent_words = function(data){
        words_count = JSON.parse(data)
        html = "<br>"
        html += "<table border='1px' >"
        words_count.forEach(function(word){
            html += "<tr><td>" + word[0] + "</td>"
            html += "<td>" + word[1] + "</td></tr>"
        })
        html += "</table>"
        $("#result")[0].innerHTML = html
    }

    var get_results = function(user_input, accurate){
      $("#result")[0].innerHTML = "Loading..."
      var xhr = new XMLHttpRequest()
      xhr.open("GET", "/api?url="+encodeURIComponent(user_input)+"&accurate="+ (accurate ? "true" : "false"), true)
      xhr.onprogress = function () {
        if ( xhr.responseText.indexOf("youtube#searchListResponse") != -1 ){
          xhr.onload = function () {
            search_json = JSON.parse( xhr.responseText )
            search_results = search_json['items'].map(function(result){
              if ( result['id']['kind'] == "youtube#video" ){
                return '<div class="search_result"><a href="https://www.youtube.com/watch?v='+result['id']['videoId']+'"><div class="thumbnail"><img src="'+result['snippet']['thumbnails']['medium']['url']+'" height="100%" alt="'+result['snippet']['title']+'"/></div><div class="content"><font size="4">'+result['snippet']['title']+'</font></div></a></div>'
              }else if ( result['id']['kind'] == "youtube#channel" ){
                return '<div class="search_result"><a href="https://www.youtube.com/channel/'+result['id']['channelId']+'"><div class="thumbnail"><img src="'+result['snippet']['thumbnails']['medium']['url']+'" height="100%" alt="'+result['snippet']['title']+'"/></div><div class="content"><font size="5">'+result['snippet']['title']+'</font></div></a></div>'
              }
            })
            $("#result")[0].innerHTML = search_results.join("\n")
            $(".search_result a").click(function (e) {
              e.preventDefault()
              get_results(e.currentTarget.href, false)
            })
          }
        }else if ( xhr.responseText.indexOf("%") != -1 ){
          percentages = xhr.responseText.replace(/\s/g,"").split("%")
          last_percentage = percentages[percentages.length-1]
          if (last_percentage){
            render_frequent_words(xhr.responseText.split("%")[percentages.length-1])
          }else{
            $("#result")[0].innerHTML = "<h3>"+percentages[percentages.length-2]+"%</h3>"
          }
        }else{
          render_frequent_words(xhr.responseText)
        }
      }
      xhr.send()
    }

    var submit = function(e){
        user_input = $('#input_channel')[0].value
        get_results(user_input, (e.target.id == "btn_accurate"))
    }

    $('#btn_submit').click(submit)
    $("#input_channel").keyup(function(e){
      if (e.keyCode == 13){
        submit(e)
      }
    })
    $('#btn_accurate').click(submit)
    $('#input_channel').bind("enterKey", submit)

})
