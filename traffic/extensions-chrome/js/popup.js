$(function () {
    chrome.storage.sync.get({identify: 'null', username: 'null', base_url: 'null'}, function (items) {
        if(items.identify === 'null'){
            $("#welcome").text("请先登录哦~");
        }else{
            $("#welcome").text("欢迎：" + items.username);
        }
    });
});