import { useEffect, useState } from 'react'
import api from "./components/api.js";
// useState lets you create state variables
  // useEffect lets you run code in response to events, such as when the first compnent renders, or state changes

import './App.css'

function App(){

  // Declare a staste viarable data with initial value null
  // setData is the function used to updata 'data'
  //const {ticker} = useParams(); 
  const [topmovers, setTopMovers] = useState([]);
  console.log(api)

  useEffect(() => {
    api.get("/topmovers")
      .then(res => {
        setTopMovers(res.data);
      })
      .catch(err => {
        console.error(err);
      });
  }, []);
  return (
    <div>
    <div className="Navbar">
      <h1 >Hello world</h1>
    </div>
    <div>
      <ul>{topmovers.map(u => (
        <li key={u.symbol}>{u.symbol} ({u.name}): ${u.price}USD <ul>
          <li> {u.change} , {u.changesPercentage}%</li>
          </ul></li>

      ))}</ul>
    </div>
    </div>
  );
}

export default App
