chrome.storage.sync.get({identify: 'null', username: 'null', base_url: 'null'}, function (items) {
    if (items.base_url === 'null') {
        alert("base_url is null!");
        return;
    }
    if (items.identify === 'null') {
        if (location.href.startsWith(items.base_url)) {  // 本站
            if (!location.href.startsWith(items.base_url + "/login")) {  // 非登录界面
                $.get(items.base_url + "/api/identify", function (data) {
                    if (data.flag === 'success') {
                        data = data.data;
                        chrome.storage.sync.set({identify: data[1], username: data[0]}, function () {
                            console.log("身份认证成功！");
                        });
                    }
                });
            }
        } else {
            location.href = items.base_url;
        }
    } else { // 流量传输

    }
});
