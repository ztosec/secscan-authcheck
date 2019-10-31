// Copyright 2018 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

'use strict';

var base_url = prompt("请输入服务器地址", "http://192.168.17.129:8888");


chrome.storage.sync.set({'base_url': base_url}, function () {
    console.log('保存成功！');
});

/**
 * 生成uri
 * @param url
 */
function gen_uri(url) {
    let matches = url.match(/http[s]?:\/\/.*?[/?](.*)/);
    let uri = "/";
    if (matches.length === 2) {
        uri += matches[1];
    }
    uri = uri.split('#', 1)[0];
    return uri;
}

/**
 * 生成header
 * @param url 默认的header中没有host，需要从url中解析一下
 * @param headers
 * @returns {string}
 */
function gen_headers(url, headers) {
    let r = "\n";
    let match = url.match(/http[s]?:\/\/(.*)/)[1];
    if (match.indexOf('/') !== -1) {
        match = match.substr(0, match.indexOf('/'));
    }
    if (match.indexOf('#') !== -1) {
        match = match.substr(0, match.indexOf('#'));
    }
    if (match.indexOf('?') !== -1) {
        match = match.substr(0, match.indexOf('?'));
    }

    r += "Host: " + match + "\n";
    headers.forEach(function (header) {
        r += header.name;
        r += ": ";
        r += header.value;
        r += "\n";
    });
    return r;
}

/**
 * 生成body
 * @param body
 * @returns {string}
 */
function gen_body(body) {
    if (body) {
        let s = "";
        try {
            if (body.raw) {
                body.raw.forEach(function (raw) {
                    if (raw.bytes) {
                        let r = new Uint8Array(raw.bytes);
                        s += String.fromCharCode.apply(null, r);
                    } else if (raw.file) { // 处理文件...
                        console.log(raw.file);
                    }
                });   
            }else{
                s = ""
                for(var nu in body.formData){
                    s += nu+"="+body.formData[nu]+"&";
                }
            }
        } catch (error) {
            console.log(error);
        }
        return s;
    }
    return "";
}

/**
 * 返回拼接后的原生流量+base64
 * @param req_body
 * @param req_header
 */
function gen_raw(req_body, req_header) {
    let raw = "";
    raw += req_body.method + " " + gen_uri(req_body.url) + " " + "HTTP/1.1";
    raw += gen_headers(req_header.url, req_header.requestHeaders);
    raw += "\n";
    raw += gen_body(req_body.requestBody);

    return $.base64.encode(raw);
}

/**
 * 通过后缀过滤流量
 * @param url
 * @returns {boolean}
 */
function filter_ext(url) {
    let ext = gen_ext(url);
    console.debug(ext + ": " + url);
    let filterExt = ["jpg", "png", "js", "css", "ico", "gif", "svg", "font"];

    let flag = false;

    filterExt.forEach(function (i) {
        if (ext.endsWith(i)) {
            flag = true;
            return flag;
        }
    });
    return flag;
}

/**
 * 生产后缀
 * @param url
 */
function gen_ext(url) {
    let path = gen_path(url);
    let dot = path.lastIndexOf('.');
    let slash = path.lastIndexOf('/');
    if (dot === -1 || dot < slash) {
        return "";
    }
    return path.substr(dot);
}

function gen_path(url) {
    let matches = url.match(/http[s]?:\/\/.*?[/](.*)/);
    if (!matches || matches.length !== 2) {
        return "/";
    }
    let path = '/' + matches[1];
    path = path.split('?', 1)[0];
    return path;
}

/**
 * 通过host过滤流量
 * @param url
 */
function filter_host(url) {
    if (url.startsWith(base_url)) {
        return true;
    }
    return false;
}

var req_bodys = {};

chrome.webRequest.onBeforeRequest.addListener(details => {
    if (!filter_ext(details.url) && !filter_host(details.url)) {
        req_bodys[details.frameId] = details;
    }
}, {urls: ["<all_urls>"]}, ["requestBody"]);

chrome.webRequest.onBeforeSendHeaders.addListener(details => {
    if (!filter_ext(details.url) && !filter_host(details.url)) {
        chrome.storage.sync.get({identify: 'null', username: 'null'}, function (items) {
            if (items.identify !== 'null') {
                let req_body = req_bodys[details.frameId];
                delete req_bodys[details.frameId];

                if (req_body) {
                    let raw = gen_raw(req_body, details);
                    console.log(raw);

                    $.post(base_url + "/api/parse", {
                        uid: items.identify,
                        url: details.url,
                        raw: raw
                    }, function (data) {
                        if (data.flag !== 'success') {
                            console.log(data.data);
                            if (data.data.indexOf("identify error") > -1) {  // 身份标识失效
                                chrome.storage.sync.set({'identify': "null", "username": "null"}, function () {
                                    console.log("身份标识删除");
                                });
                            }
                        }
                    });
                }
            }
        });
    }
}, {urls: ["<all_urls>"]}, ["requestHeaders", "extraHeaders"]);

