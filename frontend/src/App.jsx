import { useEffect, useState } from 'react'
// useState lets you create state variables
  // useEffect lets you run code in response to events, such as when the first compnent renders, or state changes

import './App.css'

function App(){

  // Declare a staste viarable data with initial value null
  // setData is the function used to updata 'data'
  //const {ticker} = useParams(); 
  const [data, setData] = useState(null);

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
}

export default App
