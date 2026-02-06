import { useEffect, useState } from 'react'
// useState lets you create state variables
  // useEffect lets you run code in response to events, such as when the first compnent renders, or state changes

import './App.css'

function App(){

  return (
    <div>
    <div className="Navbar">
      <h1 >Hello world</h1>
    </div>
    <div>
      <p> This is a paragraph</p>
    </div>
    </div>
  )
  // Declare a staste viarable data with initial value null
  // setData is the function used to updata 'data'
  //const {ticker} = useParams(); 
  const [data, setData] = useState(null);

  useEffect(() => {
    // fetch makes an http request to the backend
    fetch(`http://127.0.0.1:8000/stock/${ticker}`)
    // convert the response into JSON
    .then(res => res.json())
    // update the state variable 'data' with the fetched JSON
    .then(json => setData(json));
  }, [ticker]);

  return (
    <h1> Hello World</h1>
  )
}

export default App
