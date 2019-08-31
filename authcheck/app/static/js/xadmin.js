// Array.prototype.remove = function(val) { 
//     var index = this.indexOf(val); 
//     if (index > -1) { 
//         return  this.splice(index, 1); 
//     }

// };
$(function () {

    layui.use(['form','element'],
    function() {
        layer = layui.layer;
        element = layui.element;

        //tab 右键事件
        $(".layui-tab-title").on('contextmenu', 'li', function(event) {
            var tab_left = $(this).position().left;
            var left = $(this).position().top;
            this_index = $(this).attr('lay-id');
            $('#tab_right').css({'left':tab_left+50}).show();
            $('#tab_show').show();
            return false;
        });

        $('.page-content,#tab_show,.container,.left-nav').click(function(event) {
            $('#tab_right').hide();
            $('#tab_show').hide();
        });

        $('#tab_right').on('click', 'dd', function(event) {

            if(getCookie('tab_list')){
                var tab_list = getCookie('tab_list').split(',');
            }else{
                var tab_list = [];
            }

            var type = $(this).attr('data-type');

            if(type=='this'){

                tab.tabDelete(this_index);

                var index = -1;

                for (var i in tab_list) {
                    if(tab_list[i]==(this_index-1)){
                        index = i;
                    }
                 } 
                if (index > -1) { 
                    tab_list.splice(index, 1); 
                }

                setCookie('tab_list',tab_list);
            }
            if(type=='all'){

                for (var i in tab_list) {
                   tab.tabDelete(Number(tab_list[i])+1); 
                   tab.tabDelete(tab_list[i]);
                }

                setCookie('tab_list',[]);
            }

            if(type=='other'){

                for (var i in tab_list) {
                    if(tab_list[i]!=(this_index-1)){
                        tab.tabDelete(Number(tab_list[i])+1);
                    }
                }

                setCookie('tab_list',[this_index-1]);
            }
            // alert(this_index);
            $('#tab_right').hide();
        });

        // tab 双击事件
        $(".layui-tab-title").on('dblclick', 'li', function(event) {
            var id = $(this).attr('lay-id');
            tab.tabDelete(id);

            if(getCookie('tab_list')){
                tab_list = getCookie('tab_list').split(',');
            }else{
                tab_list = [];
            }


            var index = -1;

            for (var i in tab_list) {
                if(tab_list[i]==(id-1)){
                    index = i;
                }
             } 


            if (index > -1) { 
                tab_list.splice(index, 1); 
            }

            setCookie('tab_list',tab_list);
            return false;
        });

        // tab 删除事件
        element.on('tabDelete(xbs_tab)', function(data){
            var id  = $(this).parent().attr('lay-id')-1;

            if(getCookie('tab_list')){
                tab_list = getCookie('tab_list').split(',');
            }else{
                tab_list = [];
            }


            var index = -1;

            for (var i in tab_list) {
                if(tab_list[i]==id){
                    index = i;
                }
             } 


            if (index > -1) { 
                tab_list.splice(index, 1); 
            }

            setCookie('tab_list',tab_list);

        });

        if(getCookie('tab_list')){
            tab_list = getCookie('tab_list').split(',');

            for (var i in tab_list) {
                 $('.left-nav #nav li').eq(tab_list[i]).click();
            }
         }
    });

    //触发事件
    tab = {
        tabAdd: function(title,url,id){
          //新增一个Tab项
          element.tabAdd('xbs_tab', {
            title: title 
            ,content: '<iframe tab-id="'+id+'" frameborder="0" src="'+url+'" scrolling="yes" class="x-iframe"></iframe>'
            ,id: id
          })
        }
        ,tabDelete: function(othis){
          //删除指定Tab项
          element.tabDelete('xbs_tab', othis); //删除：“商品管理”
          
           
          // othis.addClass('layui-btn-disabled');
        }
        ,tabChange: function(id){
          //切换到指定Tab项
          element.tabChange('xbs_tab', id); //切换到：用户管理
        }
      };


    tableCheck = {
        init:function  () {
            $(".x-admin .layui-form-checkbox").click(function(event) {
                if($(this).hasClass('layui-form-checked')){
                    $(this).removeClass('layui-form-checked');
                    if($(this).hasClass('header')){
                        $(".x-admin .layui-form-checkbox").removeClass('layui-form-checked');
                    }
                }else{
                    $(this).addClass('layui-form-checked');
                    if($(this).hasClass('header')){
                        $(".x-admin .layui-form-checkbox").addClass('layui-form-checked');
                    }
                }
                
            });
        },
        getData:function  () {
            var obj = $(".x-admin .layui-form-checked").not('.header');
            var arr=[];
            obj.each(function(index, el) {
                arr.push(obj.eq(index).attr('data-id'));
            });
            return arr;
        }
    }

    // 开启表格多选
    tableCheck.init();
      

    $('.container .left_open i').click(function(event) {
        if($('.left-nav').css('left')=='0px'){
            $('.left-nav').animate({left: '-221px'}, 100);
            $('.page-content').animate({left: '0px'}, 100);
            $('.page-content-bg').hide();
        }else{
            $('.left-nav').animate({left: '0px'}, 100);
            $('.page-content').animate({left: '221px'}, 100);
            if($(window).width()<768){
                $('.page-content-bg').show();
            }
        }

    });

    $('.page-content-bg').click(function(event) {
        $('.left-nav').animate({left: '-221px'}, 100);
        $('.page-content').animate({left: '0px'}, 100);
        $(this).hide();
    });

    

    $('.layui-tab-close').click(function(event) {
        $('.layui-tab-title li').eq(0).find('i').remove();
    });

   $("tbody.x-cate tr[fid!='0']").hide();
    // 栏目多级显示效果
    $('.x-show').click(function () {
        if($(this).attr('status')=='true'){
            $(this).html('&#xe625;'); 
            $(this).attr('status','false');
            cateId = $(this).parents('tr').attr('cate-id');
            $("tbody tr[fid="+cateId+"]").show();
       }else{
            cateIds = [];
            $(this).html('&#xe623;');
            $(this).attr('status','true');
            cateId = $(this).parents('tr').attr('cate-id');
            getCateId(cateId);
            for (var i in cateIds) {
                $("tbody tr[cate-id="+cateIds[i]+"]").hide().find('.x-show').html('&#xe623;').attr('status','true');
            }
       }
    })

    //左侧菜单效果
    
    $('.left-nav #nav').on('click', 'li', function(event) {

        var index = $('.left-nav #nav li').index($(this));

        if($(this).children('.sub-menu').length){
            if($(this).hasClass('open')){

                if($(this).parent().hasClass('sub-menu')){
                    deleteCookie('left_menu_son');
                }else{
                    deleteCookie('left_menu_father');
                }

                $(this).removeClass('open');
                $(this).find('.nav_right').html('&#xe697;');
                $(this).children('.sub-menu').stop().slideUp();
                $(this).siblings().children('.sub-menu').slideUp();
            }else{
                

                if($(this).parent().hasClass('sub-menu')){
                    setCookie('left_menu_son',index);
                }else{
                    setCookie('left_menu_father',index);
                }

                $(this).addClass('open');
                $(this).children('a').find('.nav_right').html('&#xe6a6;');
                $(this).children('.sub-menu').stop().slideDown();
                $(this).siblings().children('.sub-menu').stop().slideUp();
                $(this).siblings().find('.nav_right').html('&#xe697;');
                $(this).siblings().removeClass('open');
            }
        }else{

            var url = $(this).children('a').attr('_href');
            var title = $(this).find('cite').html();
            // var index  = $('.left-nav #nav li').index($(this));

            var is_refresh = $(this).attr('date-refresh')?true:false; 

            for (var i = 0; i <$('.x-iframe').length; i++) {
                if($('.x-iframe').eq(i).attr('tab-id')==index+1){
                    tab.tabChange(index+1);
                    event.stopPropagation();

                    if(is_refresh)
                        $('.x-iframe').eq(i).attr("src",$('.x-iframe').eq(i).attr('src'));

                    return;
                }
            };
            
            if(getCookie('tab_list')){
                tab_list = getCookie('tab_list').split(',');
            }else{
                tab_list = [];
            }

            var is_exist = false;

            for (var i in tab_list) {
                if(tab_list[i]==index)
                    is_exist = true;
            }

            if(!is_exist){
                tab_list.push(index);
            }

            setCookie('tab_list',tab_list);

            tab.tabAdd(title,url,index+1);
            tab.tabChange(index+1);
        }
        
        event.stopPropagation();
         
    })

    // 左侧菜单记忆功能
    if(getCookie('left_menu_father')!=null){
        $('.left-nav #nav li').eq(getCookie('left_menu_father')).click();
    }

    if(getCookie('left_menu_son')!=null){
        $('.left-nav #nav li').eq(getCookie('left_menu_son')).click();
    }
     
     
     
    
})
var cateIds = [];
function getCateId(cateId) {
    
    $("tbody tr[fid="+cateId+"]").each(function(index, el) {
        id = $(el).attr('cate-id');
        cateIds.push(id);
        getCateId(id);
    });
}

/*弹出层*/
/*
    参数解释：
    title   标题
    url     请求的url
    id      需要操作的数据id
    w       弹出层宽度（缺省调默认值）
    h       弹出层高度（缺省调默认值）
*/
function x_admin_show(title,url,w,h,full=false){
    if (title == null || title == '') {
        title=false;
    };
    if (url == null || url == '') {
        url="404.html";
    };
    if (w == null || w == '') {
        w=($(window).width()*0.9);
    };
    if (h == null || h == '') {
        h=($(window).height() - 50);
    };
    var index = layer.open({
        type: 2,
        area: [w+'px', h +'px'],
        fix: false, //不固定
        maxmin: true,
        shadeClose: true,
        shade:0.4,
        title: title,
        content: url,
        success: function(){
          //窗口加载成功刷新frame
          // location.replace(location.href);
        },
        cancel:function(){
          //关闭窗口之后刷新frame
          // location.replace(location.href);
        },
        end:function(){
          //窗口销毁之后刷新frame
          // location.replace(location.href);
        }
    });
    if(full){
       layer.full(index); 
    }
}

/*关闭弹出框口*/
function x_admin_close(){
    var index = parent.layer.getFrameIndex(window.name);
    parent.layer.close(index);
}

function x_admin_father_reload(){
    
    parent.location.reload();
}

function x_admin_add_to_tab(title,url,is_refresh) {

    var id = md5(url);

    is_refresh =  arguments[2] ? arguments[2] : false;


    for (var i = 0; i <$('.x-iframe').length; i++) {
        if($('.x-iframe').eq(i).attr('tab-id')==id){
            tab.tabChange(id);
            // event.stopPropagation();

            if(is_refresh)
                $('.x-iframe').eq(i).attr("src",$('.x-iframe').eq(i).attr('src'));

            return;
        }
    };
    
    if(getCookie('tab_list')){
        tab_list = getCookie('tab_list').split(',');
    }else{
        tab_list = [];
    }

    var is_exist = false;

    for (var i in tab_list) {
        if(tab_list[i]==id)
            is_exist = true;
    }

    if(!is_exist){
        tab_list.push(id);
    }

    setCookie('tab_list',tab_list);

    tab.tabAdd(title,url,id);
    tab.tabChange(id);
}



