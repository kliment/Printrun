function pronterfaceWebInterface_setup(){
	pronterfaceWebInterface_attachAsync();
}

function pronterfaceWebInterface_attachAsync(){
	
	var list = [];
	if(document.getElementsByClassName){
		list = document.getElementsByClassName('command');
	}else if(document.getElementsByTagName){
		list = document.getElementsByTagName('a');
		list.concat( document.getElementsByTagName('area') );
		//TODO filter list via checking the className attributes
	}else{
		console && console.error && console.error('unable to gather list of elements');
		return false;
	}
	
	for(var i=0; i < list.length; i++){
		list[i].addEventListener && list[i].addEventListener( 'click', function(e){return pronterfaceWebInterface_asyncCommand(null, e);}, true );
		list[i].attachEvent && list[i].attachEvent( 'onclick', function(e){return pronterfaceWebInterface_asyncCommand(null, e);} );
	}
	
	return true;
}


function pronterfaceWebInterface_asyncCommand( urlOrElement, event ){

	if( ! urlOrElement && event.target)
		urlOrElement = event.target;

	var url = null;
	if( typeof urlOrElement == 'string' ){
		url = urlOrElement;
	}else{
		url = urlOrElement&&urlOrElement.href;
	}

	if( typeof url != 'string' ){
		console && console.error && console.error('url not a string', urlOrElement, url);
		return true;
	}

	var httpRequest;
	if (window.XMLHttpRequest) { // Mozilla, Safari, ...
		httpRequest = new XMLHttpRequest();
	} else if (window.ActiveXObject) { // IE 8 and older
		httpRequest = new ActiveXObject("Microsoft.XMLHTTP");
	}
	
	if( ! httpRequest ){
		alert('no AJAX available?');
		// follow link
		return true;
	}
	
	//onreadystatechange
	//onerror
	httpRequest.open( 'GET', url, true);
	httpRequest.send(null);
	
	// don't follow link
	if( event ){
		event.stopImmediatePropagation && event.stopImmediatePropagation();
		event.defaultPrevented = true;
		event.preventDefault && event.preventDefault();
	}
	return false;
}


if (document.addEventListener) {
    document.addEventListener("DOMContentLoaded", pronterfaceWebInterface_setup, false);
} else if (document.attachEvent) {
    document.attachEvent("onreadystatechange", pronterfaceWebInterface_setup);
} else {
    document.onload = pronterfaceWebInterface_setup;
}
