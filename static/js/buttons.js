// path record button
function pathRecord(element){
    var name = element.getAttribute("name");

    let formData = new FormData();
    formData.append('name', name);

    fetch('/', {
        method: 'POST',
        body: formData,
        })
    .then(function (response) {
        return response.text();
    }).then(function (text) {
        var json_data = JSON.parse(text);

        document.getElementById("record_btn").innerHTML = json_data.record_btn_msg;
    });
}
