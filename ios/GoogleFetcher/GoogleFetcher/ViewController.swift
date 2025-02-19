//
//  ViewController.swift
//  GoogleFetcher
//
//  Created by Daniel Gurbin on 18/02/2025.
//

import UIKit

class ViewController: UIViewController {

    @IBOutlet weak var textOutlet1: UITextView!
    
    
    func performHTTPCall() {
        guard let url = URL(string: "https://www.chatgpt.com") else {
            DispatchQueue.main.async {
                self.textOutlet1.text = "Invalid URL."
            }
            return
        }
        
        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    self.textOutlet1.text = "Error: \(error.localizedDescription)"
                }
                return
            }
            
            guard let data = data,
                  let responseString = String(data: data, encoding: .utf8) else {
                DispatchQueue.main.async {
                    self.textOutlet1.text = "No data received."
                }
                return
            }
            
            DispatchQueue.main.async {
                self.textOutlet1.text = responseString
            }
        }
        
        task.resume()
    }

    
    override func viewDidLoad() {
        super.viewDidLoad()
        textOutlet1.text = "loading..."
        // Do any additional setup after loading the view.
        performHTTPCall()
    }

 
    
}

