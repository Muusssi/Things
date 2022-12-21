
function toggle(class_name) {
  for (element of document.getElementsByClassName(class_name)) {
    element.hidden = !element.hidden;
  }
}

function hide(class_name) {
  for (element of document.getElementsByClassName(class_name)) {
    element.hidden = true;
  }
}

function show(class_name) {
  for (element of document.getElementsByClassName(class_name)) {
    element.hidden = false;
  }
}

function default_value(value, default_val) {
  if (value === undefined) return default_val;
  return value;
}

function option(value, name) {
  let option = document.createElement('option');
  option.innerHTML = name;
  option.value = value;
  return option;
}

function get(url, handler, async_query) {
  $.ajax(url, {
    method: 'GET',
    async: default_value(async_query, true),
    success: handler,
    error: function(jqXHR, status, error_msg) {
      console.error(url, status, error_msg);
    },
  });
}

function post(url, data, handler, async_query) {
  $.ajax(url, {
    method: 'POST',
    data: data,
    async: default_value(async_query, true),
    success: handler,
    error: function(jqXHR, status, error_msg) {
      console.error(url, status, error_msg);
    },
  });
}

