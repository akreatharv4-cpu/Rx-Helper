async function analyze(){
 let text=document.getElementById("text").value;
 let res=await fetch("http://127.0.0.1:5000/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})});
 let data=await res.json();
 document.getElementById("result").innerHTML=JSON.stringify(data,null,2);
}
